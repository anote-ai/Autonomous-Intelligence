// Flow Types
export const FlowType = {
  TRAIN: 'train',
  PREDICT: 'predict',
  EVALUATE: 'evaluate'
};

// Flow Pages
export const FlowPage = {
  FLOW_OPTIONS: 'flow_options',
  CSV_SELECTOR: 'csv_selector'
};

// NLP Tasks
export const NLPTask = {
  TEXT_CLASSIFICATION: 'text_classification',
  CHATBOT: 'chatbot', 
  PROMPTING: 'prompting',
  NER: 'ner'
};

// NLP Task Display Names
export const NLPTaskMap = {
  [NLPTask.TEXT_CLASSIFICATION]: 'Classification',
  [NLPTask.CHATBOT]: 'Chatbot',
  [NLPTask.PROMPTING]: 'Prompting',
  [NLPTask.NER]: 'NER'
};

// File Names for different tasks and flows
export const NLPTaskFileName = {
  [NLPTask.TEXT_CLASSIFICATION]: 'classification',
  [NLPTask.CHATBOT]: 'chatbot',
  [NLPTask.PROMPTING]: 'prompting',
  [NLPTask.NER]: 'ner'
};

export const FlowTypeFileName = {
  [FlowType.TRAIN]: 'train',
  [FlowType.PREDICT]: 'predict', 
  [FlowType.EVALUATE]: 'evaluate'
};

// Missing PaidUserStatus that other components need
export const PaidUserStatus = {
    FREE_TIER: 0,
    BASIC_TIER: 1,
    STANDARD_TIER: 2,
    PREMIUM_TIER: 3,
    ENTERPRISE_TIER: 4
};