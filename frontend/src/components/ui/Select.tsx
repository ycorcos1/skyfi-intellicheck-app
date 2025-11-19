import React from "react";
import styles from "./Select.module.css";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  hint?: string;
  placeholder?: string;
  options: SelectOption[];
  id: string;
  containerClassName?: string;
}

function composeClassNames(...values: Array<string | undefined | false>) {
  return values.filter(Boolean).join(" ");
}

export function Select(props: SelectProps) {
  const { label, error, hint, placeholder, options, id, className, containerClassName, ...rest } = props;

  const { value, defaultValue, ...selectRest } = rest;
  const selectAttributes: React.SelectHTMLAttributes<HTMLSelectElement> = {
    ...selectRest,
  };

  if (value !== undefined) {
    selectAttributes.value = value;
  } else if (defaultValue !== undefined) {
    selectAttributes.defaultValue = defaultValue;
  } else {
    selectAttributes.defaultValue = "";
  }

  const selectClassName = composeClassNames(styles.select, error ? styles.selectError : undefined, className);

  return (
    <div className={composeClassNames(styles.field, containerClassName)}>
      {label ? (
        <label className={styles.label} htmlFor={id}>
          {label}
        </label>
      ) : null}
      <div className={styles.wrapper}>
        <select
          id={id}
          className={selectClassName}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
          {...selectAttributes}
        >
          {placeholder ? (
            <option value="" disabled hidden>
              {placeholder}
            </option>
          ) : null}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <span aria-hidden className={styles.icon} />
      </div>
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

export default Select;

