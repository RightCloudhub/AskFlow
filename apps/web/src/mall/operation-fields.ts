import type { Operation } from "./admin-operations";
import type { OperationResource } from "./operation-records";
import type { Row } from "./shared";
import type { Field } from "./form-fields";

const PRODUCT_FIELDS = new Set(["title", "description", "code", "spu_id"]);
const REFERENCE_FIELDS = new Set(["id", "user_id", "journal_id", "role_id", "expected_version"]);

function stepTitle(operation: Operation, field: Field) {
  if (field.step) return field.step;
  if (operation.path === "/catalog/skus") return PRODUCT_FIELDS.has(field.name) ? "规格信息" : "价格设置";
  if (operation.path.startsWith("/catalog/products")) return field.name === "images" ? "商品图片" : "商品信息";
  if (operation.path === "/inventory/flash-sales") return "活动信息";
  if (REFERENCE_FIELDS.has(field.name)) return "操作对象";
  return "操作信息";
}

export function operationFields(options: {
  operation: Operation; row?: Row; resource?: OperationResource;
  roles: Array<{ value: string; label: string }>;
}): Field[] {
  const { operation, row, resource, roles } = options;
  return operation.fields.map((field) => {
    const bound = field.name === resource?.field || resource?.boundFields?.includes(field.name);
    const version = field.name === "expected_version" && row?.version !== undefined;
    const hidden = Boolean(field.hidden || (row && (bound || version)));
    const prepared = { ...field, hidden, step: stepTitle(operation, field) };
    if (field.name === "role" && operation.path === "/roles/grant") return { ...prepared, label: "授予角色", kind: "select", options: roles };
    return prepared;
  });
}
