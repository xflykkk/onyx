#!/usr/bin/env python3
"""
Script to delete qwen3-embedding-4b embedding model entries from the database
"""

import sys
import os
from sqlalchemy import create_engine, select, delete, text
from sqlalchemy.orm import sessionmaker

# Add backend directory to path
sys.path.insert(0, '/Users/zhuxiaofeng/Github/onyx/backend')

from onyx.db.models import SearchSettings, CloudEmbeddingProvider, IndexAttempt
from onyx.db.engine.sql_engine import get_sqlalchemy_engine
from onyx.db.search_settings import get_all_search_settings
from onyx.configs.app_configs import POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB


def check_qwen_embedding_models():
    """Check for qwen3-embedding-4b model entries in the database"""
    print("=== Checking for qwen3-embedding-4b model entries ===")
    
    try:
        # Get database engine
        engine = get_sqlalchemy_engine()
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        with SessionLocal() as session:
            # Query all search settings
            all_settings = session.scalars(select(SearchSettings)).all()
            
            print(f"Total search settings found: {len(all_settings)}")
            
            # Find qwen3-embedding-4b related entries
            qwen_entries = []
            for setting in all_settings:
                if 'qwen3-embedding-4b' in setting.model_name:
                    qwen_entries.append(setting)
                    print(f"Found qwen3-embedding-4b entry: ID={setting.id}, "
                          f"Model={setting.model_name}, Status={setting.status}, "
                          f"Index={setting.index_name}")
            
            if not qwen_entries:
                print("✓ No qwen3-embedding-4b entries found in database")
                return []
            
            print(f"Found {len(qwen_entries)} qwen3-embedding-4b entries")
            return qwen_entries
            
    except Exception as e:
        print(f"Error checking database: {e}")
        return []


def delete_qwen_embedding_models():
    """Delete qwen3-embedding-4b model entries from the database"""
    print("=== Deleting qwen3-embedding-4b model entries ===")
    
    try:
        # Get database engine
        engine = get_sqlalchemy_engine()
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        with SessionLocal() as session:
            # First, find all qwen3-embedding-4b entries
            qwen_settings = session.scalars(
                select(SearchSettings).where(
                    SearchSettings.model_name.like('%qwen3-embedding-4b%')
                )
            ).all()
            
            if not qwen_settings:
                print("✓ No qwen3-embedding-4b entries to delete")
                return True
            
            print(f"Found {len(qwen_settings)} qwen3-embedding-4b entries to delete:")
            for setting in qwen_settings:
                print(f"  - ID: {setting.id}, Model: {setting.model_name}, Status: {setting.status}")
            
            # Ask for confirmation
            response = input("Do you want to delete these entries? (y/N): ")
            if response.lower() != 'y':
                print("Deletion cancelled by user")
                return False
            
            # Delete associated index attempts first
            for setting in qwen_settings:
                index_attempts = session.scalars(
                    select(IndexAttempt).where(
                        IndexAttempt.search_settings_id == setting.id
                    )
                ).all()
                
                if index_attempts:
                    print(f"Deleting {len(index_attempts)} index attempts for setting {setting.id}")
                    session.execute(
                        delete(IndexAttempt).where(
                            IndexAttempt.search_settings_id == setting.id
                        )
                    )
            
            # Delete the search settings
            deleted_count = session.execute(
                delete(SearchSettings).where(
                    SearchSettings.model_name.like('%qwen3-embedding-4b%')
                )
            ).rowcount
            
            # Commit the changes
            session.commit()
            
            print(f"✓ Successfully deleted {deleted_count} qwen3-embedding-4b entries")
            return True
            
    except Exception as e:
        print(f"Error deleting entries: {e}")
        return False


def clean_orphaned_index_attempts():
    """Clean up any orphaned index attempts"""
    print("=== Cleaning orphaned index attempts ===")
    
    try:
        engine = get_sqlalchemy_engine()
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        with SessionLocal() as session:
            # Find orphaned index attempts (those referencing non-existent search settings)
            orphaned_attempts = session.execute(
                text("""
                SELECT ia.id, ia.search_settings_id 
                FROM index_attempt ia 
                LEFT JOIN search_settings ss ON ia.search_settings_id = ss.id 
                WHERE ss.id IS NULL
                """)
            ).fetchall()
            
            if orphaned_attempts:
                print(f"Found {len(orphaned_attempts)} orphaned index attempts")
                
                # Delete orphaned attempts
                session.execute(
                    text("""
                    DELETE FROM index_attempt 
                    WHERE search_settings_id NOT IN (
                        SELECT id FROM search_settings
                    )
                    """)
                )
                
                session.commit()
                print("✓ Cleaned up orphaned index attempts")
            else:
                print("✓ No orphaned index attempts found")
                
    except Exception as e:
        print(f"Error cleaning orphaned index attempts: {e}")


def main():
    """Main function to check and optionally delete qwen3-embedding-4b entries"""
    print("Qwen3-Embedding-4B Model Cleanup Tool")
    print("=" * 50)
    
    # Check for qwen entries
    qwen_entries = check_qwen_embedding_models()
    
    if not qwen_entries:
        print("No cleanup needed.")
        return
    
    print("\nOptions:")
    print("1. Delete qwen3-embedding-4b entries")
    print("2. Clean orphaned index attempts")
    print("3. Do both")
    print("4. Exit")
    
    choice = input("\nSelect option (1-4): ")
    
    if choice == '1':
        delete_qwen_embedding_models()
    elif choice == '2':
        clean_orphaned_index_attempts()
    elif choice == '3':
        delete_qwen_embedding_models()
        clean_orphaned_index_attempts()
    elif choice == '4':
        print("Exiting...")
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()