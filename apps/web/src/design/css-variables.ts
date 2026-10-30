import type { GlobalToken } from "antd";
import { BRAND, DESIGN } from "./tokens";

const px = (value: number) => `${value}px`;

export function designVariables(token: GlobalToken): Record<string, string> {
  return {
    "--bg": token.colorBgLayout,
    "--bg-tint": BRAND.frame,
    "--panel": token.colorBgContainer,
    "--panel-2": token.colorFillAlter,
    "--active": BRAND.primarySoft,
    "--ink": token.colorText,
    "--ink-2": token.colorTextSecondary,
    "--muted": token.colorTextTertiary,
    "--line": token.colorBorderSecondary,
    "--line-strong": token.colorBorder,
    "--brand": token.colorInfo,
    "--brand-strong": BRAND.accent,
    "--brand-soft": BRAND.accentSoft,
    "--brand-ink": BRAND.surface,
    "--primary": token.colorPrimary,
    "--primary-hover": token.colorPrimaryHover,
    "--success": token.colorSuccess,
    "--success-soft": BRAND.successSoft,
    "--warning": token.colorWarning,
    "--warning-soft": BRAND.warningSoft,
    "--danger": token.colorError,
    "--danger-soft": BRAND.dangerSoft,
    "--info": token.colorInfo,
    "--info-soft": BRAND.accentSoft,
    ...geometryVariables(token),
    ...syntaxVariables(token),
  };
}

function geometryVariables(token: GlobalToken): Record<string, string> {
  return {
    "--font-sans": token.fontFamily,
    "--font-mono": DESIGN.mono,
    "--radius": px(token.borderRadiusLG),
    "--radius-lg": px(token.borderRadiusLG),
    "--radius-sm": px(token.borderRadius),
    "--radius-chip": px(token.borderRadiusSM),
    "--radius-pill": px(DESIGN.radius.pill),
    "--shadow": "none",
    "--shadow-sm": "none",
    "--shadow-lg": token.boxShadowSecondary,
    "--ring": DESIGN.focusRing,
    "--dur": DESIGN.duration,
    "--space-xs": px(DESIGN.space.xs),
    "--space-sm": px(DESIGN.space.sm),
    "--space-md": px(DESIGN.space.md),
    "--space-lg": px(DESIGN.space.lg),
    "--space-xl": px(DESIGN.space.xl),
    "--space-xxl": px(DESIGN.space.xxl),
    "--space-section": px(DESIGN.space.section),
    "--fs-meta": px(DESIGN.type.meta),
    "--fs-body": px(token.fontSize),
    "--fs-reading": px(DESIGN.type.reading),
    "--fs-section": px(DESIGN.type.section),
    "--fs-title": px(token.fontSizeHeading1),
    "--fs-figure": px(DESIGN.type.figure),
    "--sidebar-width": px(DESIGN.sidebar),
    "--rail-width": px(DESIGN.rail),
    "--header-height": px(DESIGN.header),
  };
}

function syntaxVariables(token: GlobalToken): Record<string, string> {
  return {
    "--j-key": token.colorInfo,
    "--j-string": token.colorSuccess,
    "--j-number": token.colorWarning,
    "--j-boolean": token.colorError,
    "--j-null": token.colorTextTertiary,
    "--j-punct": token.colorTextTertiary,
  };
}
