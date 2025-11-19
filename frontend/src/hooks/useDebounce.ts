import { useEffect, useState } from "react";

export function useDebounce<T>(value: T, delay = 500): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handle = window.setTimeout(() => setDebouncedValue(value), delay);

    return () => {
      window.clearTimeout(handle);
    };
  }, [value, delay]);

  return debouncedValue;
}

