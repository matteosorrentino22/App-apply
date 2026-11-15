import {
  fetchCoverLetterDraftChat,
  fetchCvDraftChat,
  recordCoverLetterChatDecision,
  recordCvDraftChatDecision,
  sendCoverLetterDraftChatMessage,
  sendCvDraftChatMessage,
} from '../api/jobs'

// Chiamate della chat per `useDraftChat` (Sprint 76): stesse API di prima.
export const cvChatApi = {
  fetchChat: fetchCvDraftChat,
  sendMessage: (jobId, message, focusedBullets) => sendCvDraftChatMessage(jobId, message, focusedBullets),
  recordDecision: recordCvDraftChatDecision,
}

export const coverLetterChatApi = {
  fetchChat: fetchCoverLetterDraftChat,
  sendMessage: (jobId, message) => sendCoverLetterDraftChatMessage(jobId, message),
  recordDecision: recordCoverLetterChatDecision,
}
