import { useCallback, useState } from "react";
import type {
  QueryHistoryEntry,
  QueryResponse,
  ResultStatus,
} from "../api/types";

let nextId = 1;

export default function useQueryHistory() {
  const [history, setHistory] = useState<QueryHistoryEntry[]>([]);

  const addEntry = useCallback((query: string, response: QueryResponse) => {
    const entry: QueryHistoryEntry = {
      id: nextId++,
      query,
      route: response.route,
      result_status: response.result_status as ResultStatus,
      query_class: response.result?.query_class ?? null,
      timestamp: Date.now(),
    };
    setHistory((prev) => [entry, ...prev]);
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
  }, []);

  return { history, addEntry, clearHistory };
}
