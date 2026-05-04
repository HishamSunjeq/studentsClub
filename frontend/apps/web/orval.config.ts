import { defineConfig } from "orval";

export default defineConfig({
  studentsclub: {
    input: {
      // Dev: point at the running FastAPI server.
      // CI/offline: swap to a checked-in JSON file:
      //   target: "./openapi.json"
      target: "./openapi.json",
    },
    output: {
      mode: "tags-split",
      target: "./src/api/generated/endpoints",
      schemas: "./src/api/generated/schemas",
      client: "react-query",
      httpClient: "axios",
      prettier: true,
      clean: true,
      override: {
        mutator: {
          path: "./src/api/client.ts",
          name: "apiClient",
        },
        query: {
          useQuery: true,
          useInfinite: true,
          useMutation: true,
          signal: true,
        },
      },
    },
    hooks: {
      afterAllFilesWrite: "prettier --write",
    },
  },
});
