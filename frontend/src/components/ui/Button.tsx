import React from "react";
import styles from "./Button.module.css";

type ButtonVariant = "primary" | "secondary";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  isLoading?: boolean;
  loadingText?: string;
}

function composeClassNames(...values: Array<string | undefined | false>) {
  return values.filter(Boolean).join(" ");
}

export function Button({
  variant = "primary",
  type = "button",
  disabled,
  isLoading = false,
  loadingText,
  className,
  children,
  ...rest
}: ButtonProps) {
  const resolvedVariant: ButtonVariant = disabled ? variant : variant;
  const buttonClassName = composeClassNames(
    styles.button,
    styles[resolvedVariant],
    disabled || isLoading ? styles.disabled : undefined,
    className,
  );

  return (
    <button
      type={type}
      className={buttonClassName}
      disabled={disabled || isLoading}
      aria-busy={isLoading || undefined}
      data-loading={isLoading || undefined}
      {...rest}
    >
      {isLoading ? (
        <span className={styles.loadingContent}>
          <span className={styles.loader} aria-hidden />
          <span className={styles.loadingText}>{loadingText ?? "Processing..."}</span>
        </span>
      ) : (
        children
      )}
    </button>
  );
}

export default Button;

