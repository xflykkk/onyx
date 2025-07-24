import tempfile
import uuid
from abc import ABC
from abc import abstractmethod
from io import BytesIO
from typing import Any
from typing import cast
from typing import IO

import boto3
import puremagic
from botocore.config import Config
from botocore.exceptions import ClientError
from mypy_boto3_s3 import S3Client
from sqlalchemy.orm import Session

from onyx.configs.app_configs import AWS_REGION_NAME
from onyx.configs.app_configs import S3_AWS_ACCESS_KEY_ID
from onyx.configs.app_configs import S3_AWS_SECRET_ACCESS_KEY
from onyx.configs.app_configs import S3_ENDPOINT_URL
from onyx.configs.app_configs import S3_FILE_STORE_BUCKET_NAME
from onyx.configs.app_configs import S3_FILE_STORE_PREFIX
from onyx.configs.app_configs import S3_VERIFY_SSL
from onyx.configs.constants import FileOrigin
from onyx.db.file_record import delete_filerecord_by_file_id
from onyx.db.file_record import get_filerecord_by_file_id
from onyx.db.file_record import get_filerecord_by_file_id_optional
from onyx.db.file_record import upsert_filerecord
from onyx.db.models import FileRecord as FileStoreModel
from onyx.file_store.s3_key_utils import generate_s3_key
from onyx.utils.file import FileWithMimeType
from onyx.utils.logger import setup_logger
from shared_configs.contextvars import get_current_tenant_id

logger = setup_logger()


class FileStore(ABC):
    """
    An abstraction for storing files and large binary objects.
    """

    @abstractmethod
    def initialize(self) -> None:
        """
        Should generally be called once before any other methods are called.
        """
        raise NotImplementedError

    @abstractmethod
    def has_file(
        self,
        file_id: str,
        file_origin: FileOrigin,
        file_type: str,
    ) -> bool:
        """
        Check if a file exists in the blob store

        Parameters:
        - file_id: Unique ID of the file to check for
        - file_origin: Origin of the file
        - file_type: Type of the file
        """
        raise NotImplementedError

    @abstractmethod
    def save_file(
        self,
        content: IO,
        display_name: str | None,
        file_origin: FileOrigin,
        file_type: str,
        file_metadata: dict[str, Any] | None = None,
        file_id: str | None = None,
    ) -> str:
        """
        Save a file to the blob store

        Parameters:
        - content: Contents of the file
        - display_name: Display name of the file to save
        - file_origin: Origin of the file
        - file_type: Type of the file
        - file_metadata: Additional metadata for the file
        - file_id: Unique ID of the file to save. If not provided, a random UUID will be generated.
                   It is generally NOT recommended to provide this.

        Returns:
            The unique ID of the file that was saved.
        """
        raise NotImplementedError

    @abstractmethod
    def read_file(
        self, file_id: str, mode: str | None = None, use_tempfile: bool = False
    ) -> IO[bytes]:
        """
        Read the content of a given file by the ID

        Parameters:
        - file_id: Unique ID of file to read
        - mode: Mode to open the file (e.g. 'b' for binary)
        - use_tempfile: Whether to use a temporary file to store the contents
                        in order to avoid loading the entire file into memory

        Returns:
            Contents of the file and metadata dict
        """

    @abstractmethod
    def read_file_record(self, file_id: str) -> FileStoreModel:
        """
        Read the file record by the ID
        """

    @abstractmethod
    def delete_file(self, file_id: str) -> None:
        """
        Delete a file by its ID.

        Parameters:
        - file_name: Name of file to delete
        """

    @abstractmethod
    def get_file_with_mime_type(self, filename: str) -> FileWithMimeType | None:
        """
        Get the file + parse out the mime type.
        """


class S3BackedFileStore(FileStore):
    """Isn't necessarily S3, but is any S3-compatible storage (e.g. MinIO)"""

    def __init__(
        self,
        db_session: Session,
        bucket_name: str,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        aws_region_name: str | None = None,
        s3_endpoint_url: str | None = None,
        s3_prefix: str | None = None,
        s3_verify_ssl: bool = True,
    ) -> None:
        self.db_session = db_session
        self._s3_client: S3Client | None = None
        self._bucket_name = bucket_name
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._aws_region_name = aws_region_name or "us-east-2"
        self._s3_endpoint_url = s3_endpoint_url
        self._s3_prefix = s3_prefix or "onyx-files"
        self._s3_verify_ssl = s3_verify_ssl

    def _get_s3_client(self) -> S3Client:
        """Initialize S3 client if not already done"""
        if self._s3_client is None:
            try:
                client_kwargs: dict[str, Any] = {
                    "service_name": "s3",
                    "region_name": self._aws_region_name,
                }

                # Add endpoint URL if specified (for MinIO, etc.)
                if self._s3_endpoint_url:
                    client_kwargs["endpoint_url"] = self._s3_endpoint_url
                    client_kwargs["config"] = Config(
                        signature_version="s3v4",
                        s3={"addressing_style": "path"},  # Required for MinIO
                    )
                    # Disable SSL verification if requested (for local development)
                    if not self._s3_verify_ssl:
                        import urllib3

                        urllib3.disable_warnings(
                            urllib3.exceptions.InsecureRequestWarning
                        )
                        client_kwargs["verify"] = False

                if self._aws_access_key_id and self._aws_secret_access_key:
                    # Use explicit credentials
                    client_kwargs.update(
                        {
                            "aws_access_key_id": self._aws_access_key_id,
                            "aws_secret_access_key": self._aws_secret_access_key,
                        }
                    )
                    self._s3_client = boto3.client(**client_kwargs)
                else:
                    # Use IAM role or default credentials (not typically used with MinIO)
                    self._s3_client = boto3.client(**client_kwargs)

            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
                raise RuntimeError(f"Failed to initialize S3 client: {e}")

        return self._s3_client

    def _get_bucket_name(self) -> str:
        """Get S3 bucket name from configuration"""
        if not self._bucket_name:
            raise RuntimeError("S3 bucket name is required for S3 file store")
        return self._bucket_name

    def _get_s3_key(self, file_name: str) -> str:
        """Generate S3 key from file name with tenant ID prefix"""
        tenant_id = get_current_tenant_id()

        s3_key = generate_s3_key(
            file_name=file_name,
            prefix=self._s3_prefix,
            tenant_id=tenant_id,
            max_key_length=1024,
        )

        # Log if truncation occurred (when the key is exactly at the limit)
        if len(s3_key) == 1024:
            logger.info(f"File name was too long and was truncated: {file_name}")

        return s3_key

    def initialize(self) -> None:
        """Initialize the S3 file store by ensuring the bucket exists"""
        s3_client = self._get_s3_client()
        bucket_name = self._get_bucket_name()

        # Check if bucket exists
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            logger.info(f"S3 bucket '{bucket_name}' already exists")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                # Bucket doesn't exist, create it
                logger.info(f"Creating S3 bucket '{bucket_name}'")

                # For AWS S3, we need to handle region-specific bucket creation
                region = (
                    s3_client._client_config.region_name
                    if hasattr(s3_client, "_client_config")
                    else None
                )

                if region and region != "us-east-1":
                    # For regions other than us-east-1, we need to specify LocationConstraint
                    s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={"LocationConstraint": region},
                    )
                else:
                    # For us-east-1 or MinIO/other S3-compatible services
                    s3_client.create_bucket(Bucket=bucket_name)

                logger.info(f"Successfully created S3 bucket '{bucket_name}'")
            elif error_code == "403":
                # Bucket exists but we don't have permission to access it
                logger.warning(
                    f"S3 bucket '{bucket_name}' exists but access is forbidden"
                )
                raise RuntimeError(
                    f"Access denied to S3 bucket '{bucket_name}'. Check credentials and permissions."
                )
            else:
                # Some other error occurred
                logger.error(f"Failed to check S3 bucket '{bucket_name}': {e}")
                raise RuntimeError(f"Failed to check S3 bucket '{bucket_name}': {e}")

    def has_file(
        self,
        file_id: str,
        file_origin: FileOrigin,
        file_type: str,
    ) -> bool:
        file_record = get_filerecord_by_file_id_optional(
            file_id=file_id, db_session=self.db_session
        )
        return (
            file_record is not None
            and file_record.file_origin == file_origin
            and file_record.file_type == file_type
        )

    def save_file(
        self,
        content: IO,
        display_name: str | None,
        file_origin: FileOrigin,
        file_type: str,
        file_metadata: dict[str, Any] | None = None,
        file_id: str | None = None,
    ) -> str:
        if file_id is None:
            file_id = str(uuid.uuid4())

        s3_client = self._get_s3_client()
        bucket_name = self._get_bucket_name()
        s3_key = self._get_s3_key(file_id)

        # Read content from IO object
        if hasattr(content, "read"):
            file_content = content.read()
            if hasattr(content, "seek"):
                content.seek(0)  # Reset position for potential re-reads
        else:
            file_content = content

        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=file_content,
            ContentType=file_type,
        )

        # Save metadata to database
        upsert_filerecord(
            file_id=file_id,
            display_name=display_name or file_id,
            file_origin=file_origin,
            file_type=file_type,
            bucket_name=bucket_name,
            object_key=s3_key,
            db_session=self.db_session,
            file_metadata=file_metadata,
        )
        self.db_session.commit()

        return file_id

    def read_file(
        self, file_id: str, mode: str | None = None, use_tempfile: bool = False
    ) -> IO[bytes]:
        file_record = get_filerecord_by_file_id(
            file_id=file_id, db_session=self.db_session
        )

        s3_client = self._get_s3_client()
        try:
            response = s3_client.get_object(
                Bucket=file_record.bucket_name, Key=file_record.object_key
            )
        except ClientError:
            logger.error(f"Failed to read file {file_id} from S3")
            raise

        file_content = response["Body"].read()

        if use_tempfile:
            # Always open in binary mode for temp files since we're writing bytes
            temp_file = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
            temp_file.write(file_content)
            temp_file.seek(0)
            return temp_file
        else:
            return BytesIO(file_content)

    def read_file_record(self, file_id: str) -> FileStoreModel:
        file_record = get_filerecord_by_file_id(
            file_id=file_id, db_session=self.db_session
        )
        return file_record

    def delete_file(self, file_id: str) -> None:
        try:
            file_record = get_filerecord_by_file_id(
                file_id=file_id, db_session=self.db_session
            )

            # Delete from external storage
            s3_client = self._get_s3_client()
            s3_client.delete_object(
                Bucket=file_record.bucket_name, Key=file_record.object_key
            )

            # Delete metadata from database
            delete_filerecord_by_file_id(file_id=file_id, db_session=self.db_session)

            self.db_session.commit()

        except Exception:
            self.db_session.rollback()
            raise

    def get_file_with_mime_type(self, filename: str) -> FileWithMimeType | None:
        mime_type: str = "application/octet-stream"
        try:
            file_io = self.read_file(filename, mode="b")
            file_content = file_io.read()
            matches = puremagic.magic_string(file_content)
            if matches:
                mime_type = cast(str, matches[0].mime_type)
            return FileWithMimeType(data=file_content, mime_type=mime_type)
        except Exception:
            return None


def get_s3_file_store(db_session: Session) -> S3BackedFileStore:
    """
    Returns the S3 file store implementation.
    """

    # Get bucket name - this is required
    bucket_name = S3_FILE_STORE_BUCKET_NAME
    if not bucket_name:
        raise RuntimeError(
            "S3_FILE_STORE_BUCKET_NAME configuration is required for S3 file store"
        )

    return S3BackedFileStore(
        db_session=db_session,
        bucket_name=bucket_name,
        aws_access_key_id=S3_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=S3_AWS_SECRET_ACCESS_KEY,
        aws_region_name=AWS_REGION_NAME,
        s3_endpoint_url=S3_ENDPOINT_URL,
        s3_prefix=S3_FILE_STORE_PREFIX,
        s3_verify_ssl=S3_VERIFY_SSL,
    )


def get_default_file_store(db_session: Session) -> FileStore:
    """
    Returns the configured file store implementation.

    Supports Qiniu Cloud, AWS S3, MinIO, and other S3-compatible storage.

    Configuration is handled via environment variables defined in app_configs.py:

    Qiniu Cloud (Default):
    - QINIU_DEFAULT_BUCKET=<bucket-name>
    - QINIU_ACCESS_KEY=<access-key>
    - QINIU_SECRET_KEY=<secret-key>
    - QINIU_BUCKET_DOMAIN=<bucket-domain>
    - QINIU_REGION=<region> (optional, defaults to 'cn-east-1')

    AWS S3:
    - S3_FILE_STORE_BUCKET_NAME=<bucket-name>
    - S3_FILE_STORE_PREFIX=<prefix> (optional, defaults to 'onyx-files')
    - AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY (or use IAM roles)
    - AWS_REGION_NAME=<region> (optional, defaults to 'us-east-2')

    MinIO:
    - S3_FILE_STORE_BUCKET_NAME=<bucket-name>
    - S3_ENDPOINT_URL=<minio-endpoint> (e.g., http://localhost:9000)
    - MINIO_ACCESS_KEY=<minio-access-key> (falls back to AWS_ACCESS_KEY_ID)
    - MINIO_SECRET_KEY=<minio-secret-key> (falls back to AWS_SECRET_ACCESS_KEY)
    - AWS_REGION_NAME=<any-region> (optional, defaults to 'us-east-2')
    - S3_VERIFY_SSL=false (optional, for local development)

    Other S3-compatible storage (Digital Ocean, Linode, etc.):
    - Same as MinIO, but set appropriate S3_ENDPOINT_URL
    """
    from onyx.configs.app_configs import (
        QINIU_DEFAULT_BUCKET,
        QINIU_ACCESS_KEY,
        QINIU_SECRET_KEY,
        QINIU_BUCKET_DOMAIN,
    )
    
    # 优先使用 S3/MinIO（如果配置了 S3_FILE_STORE_BUCKET_NAME）
    if S3_FILE_STORE_BUCKET_NAME:
        return get_s3_file_store(db_session)
    
    # 回退到七牛云（如果配置了七牛云）
    if QINIU_DEFAULT_BUCKET and QINIU_ACCESS_KEY and QINIU_SECRET_KEY and QINIU_BUCKET_DOMAIN:
        from onyx.file_store.qiniu_file_store import get_qiniu_file_store
        return get_qiniu_file_store(db_session)
    
    # 如果都没有配置，抛出错误
    raise RuntimeError("No file store configured. Please configure either S3 or Qiniu Cloud storage.")
