export const queryKeys = {
  auth: {
    me: () => ["users", "me"] as const,
  },
  subjects: {
    all: (params?: object) => ["subjects", params] as const,
    mine: (params?: object) => ["subjects", "me", params] as const,
    detail: (id: string) => ["subjects", id] as const,
  },
  uploads: {
    detail: (id: string) => ["uploads", id] as const,
  },
  questionSets: {
    mine: (params?: object) => ["question-sets", "me", params] as const,
    detail: (id: string) => ["question-sets", id] as const,
  },
  quizzes: {
    mine: (params?: object) => ["quizzes", "me", params] as const,
    detail: (id: string) => ["quizzes", id] as const,
    withQuestions: (id: string) => ["quizzes", id, "questions"] as const,
  },
} as const;
