import { callGroups, calls } from "@/lib/mock-data";

export const callsRepository = {
  getAll() {
    return calls;
  },
  getById(id: string) {
    return calls.find((call) => call.id === id) ?? null;
  },
  getGroups() {
    return callGroups;
  },
};
