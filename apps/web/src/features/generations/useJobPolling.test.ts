import { describe, expect, it } from "vitest";

import { jobPollingInterval } from "./useJobPolling";

describe("jobPollingInterval", () => {
  it("stops for hidden, paused and terminal jobs", () => {
    expect(jobPollingInterval({ pause: false, hidden: true, state: "queued", failureCount: 0 })).toBe(false);
    expect(jobPollingInterval({ pause: true, hidden: false, state: "queued", failureCount: 0 })).toBe(false);
    expect(jobPollingInterval({ pause: false, hidden: false, state: "succeeded", failureCount: 0 })).toBe(false);
  });

  it("backs off failed reads with a finite cap", () => {
    expect(jobPollingInterval({ pause: false, hidden: false, state: "queued", failureCount: 0 })).toBe(1_000);
    expect(jobPollingInterval({ pause: false, hidden: false, state: "queued", failureCount: 2 })).toBe(4_000);
    expect(jobPollingInterval({ pause: false, hidden: false, state: "queued", failureCount: 12 })).toBe(30_000);
  });
});
