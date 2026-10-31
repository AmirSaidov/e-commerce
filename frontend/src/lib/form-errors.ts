import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import type { ApiError } from "@/lib/api";

/**
 * Раскладывает ошибки валидации DRF ({"fields": {"email": ["..."]}}) по полям формы.
 * Возвращает true, если хотя бы одна ошибка нашла своё поле.
 */
export function applyServerErrors<T extends FieldValues>(
  error: ApiError,
  setError: UseFormSetError<T>,
): boolean {
  let applied = false;
  for (const [field, messages] of Object.entries(error.fields)) {
    if (!messages.length) continue;
    setError(field as Path<T>, { type: "server", message: messages[0] });
    applied = true;
  }
  return applied;
}
