import { z } from "zod";

// Правила пароля совпадают с AUTH_PASSWORD_VALIDATORS на бэкенде (минимум 8 символов, не только цифры).
export const passwordSchema = z
  .string()
  .min(8, "Минимум 8 символов")
  .regex(/\D/, "Пароль не может состоять только из цифр");

export const emailSchema = z.email("Введите корректный email");

export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, "Введите пароль"),
});

export const registerSchema = z
  .object({
    first_name: z.string().trim().min(1, "Введите имя").max(50),
    last_name: z.string().trim().min(1, "Введите фамилию").max(50),
    email: emailSchema,
    password: passwordSchema,
    password_confirm: z.string(),
  })
  .refine((d) => d.password === d.password_confirm, {
    path: ["password_confirm"],
    message: "Пароли не совпадают",
  });

export const profileSchema = z.object({
  first_name: z.string().trim().min(1, "Введите имя").max(50),
  last_name: z.string().trim().min(1, "Введите фамилию").max(50),
  phone: z
    .string()
    .trim()
    .regex(/^\+?[\d\s()-]{10,20}$/, "Введите телефон, например +7 700 123 45 67")
    .or(z.literal("")),
});

export const changePasswordSchema = z
  .object({
    old_password: z.string().min(1, "Введите текущий пароль"),
    new_password: passwordSchema,
    new_password_confirm: z.string(),
  })
  .refine((d) => d.new_password === d.new_password_confirm, {
    path: ["new_password_confirm"],
    message: "Пароли не совпадают",
  });
