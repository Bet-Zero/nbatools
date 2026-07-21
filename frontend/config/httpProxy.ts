import publicHttpContract from "../../contracts/public_http_routes.json";

const API_TARGET = "http://127.0.0.1:8000";

export const PUBLIC_API_PROXY = Object.fromEntries(
  [...publicHttpContract.public_routes]
    .sort((left, right) => right.path.length - left.path.length)
    .map(({ path }) => [path, API_TARGET]),
);

export const LOCAL_ONLY_API_PROXY = {
  "/api/dev/fixtures": API_TARGET,
  "/api/admin/feedback": API_TARGET,
};

export const VITE_API_PROXY = {
  ...PUBLIC_API_PROXY,
  ...LOCAL_ONLY_API_PROXY,
};
