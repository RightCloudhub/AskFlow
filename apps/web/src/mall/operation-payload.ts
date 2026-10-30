import type { Operation } from "./admin-operations";

/** Keep UI-only state out of strict command schemas and encode path parameters. */
export function operationPayload(options: {
  operation: Operation; values: Record<string, unknown>; token: string; record?: Record<string, unknown>;
}) {
  const { operation, values, token } = options;
  const body: Record<string, unknown> = Object.fromEntries(operation.fields
    .filter((field) => field.name in values).map((field) => [field.name, values[field.name]]));
  if (operation.fields.some((field) => field.name === "permissions")) body.permissions ??= [];
  if (operation.fields.some((field) => field.name === "channels")) body.channels ??= [];
  if ("images" in body) body.images = String(body.images ?? "").split(",").map((value) => value.trim()).filter(Boolean);
  if (operation.purpose) body.step_up_token = token;
  if (operation.path === "/catalog/products/:id" && options.record) {
    body.category_id = options.record.category_id ?? null;
    body.attributes = options.record.attributes ?? {};
  }
  const path = operation.path.replace(/:([a-z_]+)/g, (_match, key: string) => {
    const value = body[key];
    delete body[key];
    return encodeURIComponent(String(value ?? ""));
  });
  return { path: "/api/v1/admin/mall" + path, body, method: operation.method };
}
