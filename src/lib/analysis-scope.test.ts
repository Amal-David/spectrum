import { describe, expect, it } from "vitest";

import {
  buildAnalysisHref,
  parseAnalysisScope,
  parseCallIdsFromSearchParams,
} from "@/lib/analysis-scope";

describe("analysis scope helpers", () => {
  it("defaults to the first call when no query parameters are present", () => {
    const scope = parseAnalysisScope({});

    expect(scope.kind).toBe("single");
    expect(scope.callIds).toEqual(["call-001"]);
  });

  it("parses multiple selected calls from the query string", () => {
    const callIds = parseCallIdsFromSearchParams({
      calls: "call-001,call-003,call-005",
    });

    expect(callIds).toEqual(["call-001", "call-003", "call-005"]);
  });

  it("builds a grouped analysis scope when multiple calls are selected", () => {
    const scope = parseAnalysisScope({
      calls: "call-001,call-006",
    });

    expect(scope.kind).toBe("group");
    expect(scope.callIds).toEqual(["call-001", "call-006"]);
    expect(scope.label).toBe("Pricing friction cluster");
  });

  it("builds a single-call analysis link", () => {
    expect(buildAnalysisHref(["call-003"])).toBe("/analysis?callId=call-003");
  });

  it("builds a grouped analysis link", () => {
    expect(buildAnalysisHref(["call-001", "call-005"])).toBe(
      "/analysis?calls=call-001%2Ccall-005"
    );
  });
});
