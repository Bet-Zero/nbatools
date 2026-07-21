import { describe, expect, it } from "vitest";
import publicHttpContract from "../../contracts/public_http_routes.json";
import {
  LOCAL_ONLY_API_PROXY,
  PUBLIC_API_PROXY,
  VITE_API_PROXY,
} from "./httpProxy";

describe("Vite public HTTP proxy contract", () => {
  it("proxies every contracted public route and orders longer prefixes first", () => {
    expect(Object.keys(PUBLIC_API_PROXY).sort()).toEqual(
      publicHttpContract.public_routes.map(({ path }) => path).sort(),
    );
    expect(new Set(Object.values(PUBLIC_API_PROXY))).toEqual(
      new Set(["http://127.0.0.1:8000"]),
    );
    expect(Object.keys(PUBLIC_API_PROXY).indexOf("/query-feedback")).toBeLessThan(
      Object.keys(PUBLIC_API_PROXY).indexOf("/query"),
    );
  });

  it("keeps operator-only proxies separate from the public contract", () => {
    expect(Object.keys(LOCAL_ONLY_API_PROXY).sort()).toEqual([
      "/api/admin/feedback",
      "/api/dev/fixtures",
    ]);
    expect(
      publicHttpContract.intentional_differences.fastapi_local_only_routes,
    ).toContain("/api/dev/fixtures");
    expect(
      publicHttpContract.intentional_differences.fastapi_local_only_routes,
    ).toContain("/api/admin/feedback/*");
    expect(VITE_API_PROXY).toEqual({
      ...PUBLIC_API_PROXY,
      ...LOCAL_ONLY_API_PROXY,
    });
  });
});
