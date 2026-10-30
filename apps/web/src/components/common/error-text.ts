const ERROR_MESSAGES: Record<string, string> = {
  invalid_credentials: "账号或密码不正确，请检查后重试。",
  account_inactive: "账号已停用，请联系管理员。",
  authentication_required: "登录已失效，请重新登录。",
  recent_login_required: "本次操作需要重新登录后完成。",
  permission_denied: "当前账号没有此操作的权限。",
  registration_disabled: "当前未开放自助注册，请联系管理员。",
  password_policy_failed: "密码至少需要 12 位，包含大写字母、小写字母和数字。",
  password_breach_check_failed: "密码安全检查暂时不可用，请稍后重试。",
  verification_invalid: "验证码不正确或已失效，请重新发送。",
  verification_rate_limited: "验证码发送过于频繁，请稍后再试。",
  verification_target_invalid: "请检查邮箱或包含国家区号的手机号。",
  verified_contact_required: "请先完成邮箱或手机验证。",
  step_up_required: "身份验证已失效，请重新确认身份。",
  mfa_setup_required: "请先设置验证器，再启用二步验证。",
  mfa_already_enabled: "二步验证已开启，请刷新查看。",
  binding_unavailable: "该联系方式暂时无法绑定，请检查后重试。",
  version_conflict: "资料已被更新，请刷新后重新修改。",
  resource_not_found: "该记录已不存在，请刷新查看。",
  resource_busy: "该记录正在处理，请稍后重试。",
  dependency_unavailable: "相关服务暂时不可用，请稍后重试。",
  capability_unavailable: "当前部署未启用此功能。",
  inventory_insufficient: "商品库存不足，请调整数量或重新选购。",
  product_unavailable: "商品已下架或暂不可购买，请重新选购。",
  price_unavailable: "商品价格已变化，请重新核对金额。",
  invalid_quantity: "商品数量无效，请重新填写。",
  cart_item_limit: "购物车商品数量已达到上限，请先结算或移除部分商品。",
  checkout_expired_or_used: "结算信息已失效，请重新核对金额。",
  checkout_invalid: "结算信息不完整，请检查商品与收货地址。",
  confirmation_invalid: "确认信息已失效，请重新发起此操作。",
  order_expired: "订单已过期，请重新下单。",
  order_not_payable: "当前订单状态不支持支付，请刷新查看。",
  order_not_refundable: "当前订单状态不支持退款，请联系订单客服。",
  invalid_order_transition: "订单状态已变化，请刷新后重新操作。",
  payment_gateway_unavailable: "支付服务暂时不可用，请稍后重试。",
  wallet_insufficient: "钱包可用余额不足，请调整抵扣金额。",
  wallet_balance_limit: "钱包余额将超过允许上限，请调整金额。",
  wallet_not_empty: "钱包仍有余额或冻结资金，结清后才能注销账号。",
  unfinished_orders: "仍有未完成的订单，请处理后再注销账号。",
  unfinished_payments: "仍有待处理的支付，请处理后再注销账号。",
  invalid_amount: "金额无效，请填写有效金额。",
  payment_amount_invalid: "支付金额无效，请重新核对订单。",
  refund_exceeds_payment: "退款金额超过可退金额，请重新填写。",
  upload_size_invalid: "文件大小不符合要求，请重新选择文件。",
  upload_type_invalid: "文件格式不支持，请选择允许的格式。",
  payload_too_large: "提交内容过大，请减少内容后重试。",
  invalid_invitation: "邀请码无效，请检查邀请码或留空后注册。",
  csrf_invalid: "登录验证已失效，请刷新页面后重新操作。",
  idempotency_in_progress: "请求正在处理，请稍后刷新查看结果。",
  idempotency_conflict: "请求内容已变化，请刷新后重新提交。",
  dual_control_required: "此操作需要另一位有权限的管理员复核。",
  cannot_disable_self: "无法停用当前登录账号。",
};
const FALLBACK = "操作未完成，请稍后重试。";
const NETWORK_ERRORS = new Set(["Failed to fetch", "fetch failed", "NetworkError when attempting to fetch resource.", "Load failed"]);

function plainMessage(value: string) {
  const text = value.trim();
  if (NETWORK_ERRORS.has(text)) return "无法连接服务，请检查网络后重试。";
  return ERROR_MESSAGES[text.replace(/ /g, "_")] ?? (text || FALLBACK);
}

function objectMessage(value: Record<string, unknown>) {
  if (typeof value.code === "string" && ERROR_MESSAGES[value.code]) return ERROR_MESSAGES[value.code];
  if (typeof value.detail === "string") return plainMessage(value.detail);
  if (typeof value.message === "string") return plainMessage(value.message);
  if (Array.isArray(value.detail)) return "提交内容不完整或格式有误，请检查字段提示。";
  return FALLBACK;
}

function parsedMessage(raw: string) {
  try {
    const parsed: unknown = JSON.parse(raw);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return objectMessage(parsed as Record<string, unknown>);
  } catch { /* A plain service message does not need JSON decoding. */ }
  return plainMessage(raw);
}

export function readableError(error: unknown): string {
  if (error instanceof Error) return parsedMessage(error.message);
  if (error && typeof error === "object") return objectMessage(error as Record<string, unknown>);
  return parsedMessage(String(error ?? ""));
}
