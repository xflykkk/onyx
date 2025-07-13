import { useState, useCallback } from 'react';
import { 
  SubQuestionDetail, 
  SubQueryDetail, 
  StreamingDetail,
  SubQuestionPiece,
  SubQueryPiece,
  AgentAnswerPiece,
  SubQuestionSearchDoc,
  StreamStopInfo,
  OnyxDocument
} from '@/types';

// Utility function to clean HTML tags from text
export function cleanSubQuestionText(text: string): string {
  if (!text) return '';
  // Remove <sub-question> and </sub-question> tags
  let cleaned = text.replace(/<\/?sub-question>/g, '');
  // Remove <query> and </query> tags
  cleaned = cleaned.replace(/<\/?query>/g, '');
  // Remove any other HTML-like tags that might appear
  cleaned = cleaned.replace(/<[^>]*>/g, '');
  // Remove multiple spaces and trim
  cleaned = cleaned.replace(/\s+/g, ' ').trim();
  return cleaned;
}

// Function to construct sub-questions from streaming data
export function constructSubQuestions(
  subQuestions: SubQuestionDetail[],
  newDetail: StreamingDetail
): SubQuestionDetail[] {
  if (!newDetail) {
    return subQuestions;
  }

  // Skip level 0, question 0 as it's typically the main question
  if (newDetail.level_question_num === 0) {
    return subQuestions;
  }

  const updatedSubQuestions = [...subQuestions];

  // Handle stop reason
  if ('stop_reason' in newDetail) {
    const { level, level_question_num } = newDetail;
    const subQuestion = updatedSubQuestions.find(
      (sq) => sq.level === level && sq.level_question_num === level_question_num
    );
    if (subQuestion) {
      if (newDetail.stream_type === "sub_answer") {
        subQuestion.answer_streaming = false;
        subQuestion.is_complete = true; // 子答案完成时也标记为完成
      } else {
        subQuestion.is_complete = true;
        subQuestion.is_stopped = true;
      }
    }
    return updatedSubQuestions;
  }

  // Handle documents
  if ('top_documents' in newDetail) {
    const { level, level_question_num, top_documents } = newDetail;
    let subQuestion = updatedSubQuestions.find(
      (sq) => sq.level === level && sq.level_question_num === level_question_num
    );
    if (!subQuestion) {
      subQuestion = {
        level: level ?? 0,
        level_question_num: level_question_num ?? 0,
        question: "",
        answer: "",
        sub_queries: [],
        context_docs: { top_documents },
        is_complete: false,
      };
      updatedSubQuestions.push(subQuestion);
    } else {
      subQuestion.context_docs = { top_documents };
    }
    return updatedSubQuestions;
  }

  // Handle answer pieces
  if ('answer_piece' in newDetail) {
    const { level, level_question_num, answer_piece } = newDetail;
    let subQuestion = updatedSubQuestions.find(
      (sq) => sq.level === level && sq.level_question_num === level_question_num
    );

    if (!subQuestion) {
      subQuestion = {
        level,
        level_question_num,
        question: "",
        answer: "",
        sub_queries: [],
        context_docs: undefined,
        is_complete: false,
      };
      updatedSubQuestions.push(subQuestion);
    }

    // Append to the answer
    subQuestion.answer = (subQuestion.answer || "") + answer_piece;
    subQuestion.answer_streaming = true;
    return updatedSubQuestions;
  }

  // Handle sub-question pieces
  if ('sub_question' in newDetail) {
    const { level, level_question_num, sub_question } = newDetail;

    let subQuestion = updatedSubQuestions.find(
      (sq) => sq.level === level && sq.level_question_num === level_question_num
    );

    if (!subQuestion) {
      subQuestion = {
        level,
        level_question_num,
        question: "",
        answer: "",
        sub_queries: [],
        context_docs: undefined,
        is_complete: false,
      };
      updatedSubQuestions.push(subQuestion);
    }

    // Append to the question
    subQuestion.question = (subQuestion.question || "") + sub_question;
    return updatedSubQuestions;
  }

  // Handle sub-query pieces
  if ('sub_query' in newDetail && 'query_id' in newDetail) {
    const { level, level_question_num, query_id, sub_query } = newDetail;

    let subQuestion = updatedSubQuestions.find(
      (sq) => sq.level === level && sq.level_question_num === level_question_num
    );

    if (!subQuestion) {
      subQuestion = {
        level,
        level_question_num,
        question: "",
        answer: "",
        sub_queries: [],
        context_docs: undefined,
        is_complete: false,
      };
      updatedSubQuestions.push(subQuestion);
    }

    // Find or create the relevant SubQueryDetail
    let subQueryDetail = subQuestion.sub_queries?.find(
      (sq) => sq.query_id === query_id
    );

    if (!subQueryDetail) {
      subQueryDetail = { query: "", query_id: query_id ?? 0 };
      subQuestion.sub_queries = [...(subQuestion.sub_queries || []), subQueryDetail];
    }

    // Append to the query
    subQueryDetail.query = (subQueryDetail.query || "") + sub_query;
    return updatedSubQuestions;
  }

  return updatedSubQuestions;
}

// Hook for managing streaming sub-questions
export function useStreamingSubQuestions(
  initialSubQuestions: SubQuestionDetail[] = []
) {
  const [subQuestions, setSubQuestions] = useState<SubQuestionDetail[]>(initialSubQuestions);

  const updateSubQuestions = useCallback((newDetail: StreamingDetail) => {
    setSubQuestions(prev => constructSubQuestions(prev, newDetail));
  }, []);

  const resetSubQuestions = useCallback(() => {
    setSubQuestions([]);
  }, []);

  return {
    subQuestions,
    updateSubQuestions,
    resetSubQuestions,
    setSubQuestions,
  };
}