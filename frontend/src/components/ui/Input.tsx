import React from "react";
import styles from "./Input.module.css";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
  id: string;
  containerClassName?: string;
}

function composeClassNames(...values: Array<string | undefined | false>) {
  return values.filter(Boolean).join(" ");
}

export function Input({
  label,
  error,
  hint,
  id,
  className,
  containerClassName,
  ...rest
}: InputProps) {
  const inputClassName = composeClassNames(styles.input, error ? styles.inputError : undefined, className);

  return (
    <div className={composeClassNames(styles.field, containerClassName)}>
      {label ? (
        <label className={styles.label} htmlFor={id}>
          {label}
        </label>
      ) : null}
      <input id={id} className={inputClassName} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined} {...rest} />
      {hint && !error ? (
        <p id={`${id}-hint`} className={styles.hint}>
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={`${id}-error`} role="alert" className={styles.error}>
          {error}
        </p>
      ) : null}
    </div>
  );
}

export default Input;

