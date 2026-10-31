"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useInfiniteQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ImagePlus, MessageSquare, Star, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Field, Textarea } from "@/components/ui/input";
import { EmptyState, Skeleton } from "@/components/ui/misc";
import { ApiError, api } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";
import { Stars } from "./price";

const MAX_IMAGES = 5;
const MAX_IMAGE_SIZE = 5 * 1024 * 1024;
const IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];

const reviewSchema = z.object({
  rating: z.number().int().min(1, "Поставьте оценку").max(5),
  text: z.string().trim().min(10, "Напишите хотя бы пару предложений").max(2000),
  images: z
    .array(z.instanceof(File))
    .max(MAX_IMAGES, `Не больше ${MAX_IMAGES} фото`)
    .refine((files) => files.every((f) => f.size <= MAX_IMAGE_SIZE), "Каждое фото — до 5 МБ")
    .refine(
      (files) => files.every((f) => IMAGE_TYPES.includes(f.type)),
      "Только JPG, PNG или WebP",
    ),
});
type ReviewForm = z.infer<typeof reviewSchema>;

function RatingInput({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const [hover, setHover] = useState(0);
  return (
    <div
      className="flex gap-1"
      role="radiogroup"
      aria-label="Оценка"
      onMouseLeave={() => setHover(0)}
    >
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          type="button"
          role="radio"
          aria-checked={value === n}
          aria-label={`${n} из 5`}
          onClick={() => onChange(n)}
          onMouseEnter={() => setHover(n)}
          className="rounded p-0.5"
        >
          <Star
            className={cn(
              "size-7 transition-colors",
              n <= (hover || value) ? "fill-warning text-warning" : "text-input",
            )}
          />
        </button>
      ))}
    </div>
  );
}

function ReviewFormBlock({ slug, onDone }: { slug: string; onDone: () => void }) {
  const queryClient = useQueryClient();
  const {
    register,
    control,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<ReviewForm>({
    resolver: zodResolver(reviewSchema),
    defaultValues: { rating: 0, text: "", images: [] },
  });
  const images = watch("images");

  const mutation = useMutation({
    mutationFn: (data: ReviewForm) => api.reviews.create(slug, data),
    onSuccess: () => {
      toast.success("Спасибо за отзыв!");
      void queryClient.invalidateQueries({ queryKey: ["reviews", slug] });
      onDone();
    },
    onError: (error) =>
      toast.error(error instanceof ApiError ? error.message : "Не удалось отправить отзыв"),
  });

  return (
    <form
      onSubmit={handleSubmit((data) => mutation.mutate(data))}
      className="bg-card space-y-4 rounded-2xl border p-5"
      noValidate
    >
      <div className="grid gap-1.5">
        <span className="text-sm font-medium">Ваша оценка</span>
        <Controller
          control={control}
          name="rating"
          render={({ field }) => <RatingInput value={field.value} onChange={field.onChange} />}
        />
        {errors.rating && <p className="text-destructive text-xs">{errors.rating.message}</p>}
      </div>
      <Field label="Отзыв" htmlFor="review-text" error={errors.text?.message}>
        <Textarea
          id="review-text"
          rows={4}
          placeholder="Что понравилось, что нет? Как товар показал себя в деле?"
          aria-invalid={!!errors.text}
          {...register("text")}
        />
      </Field>
      <div className="space-y-2">
        <div className="flex flex-wrap gap-2">
          {images.map((file, i) => (
            <span
              key={`${file.name}-${i}`}
              className="bg-muted inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs"
            >
              {file.name}
              <button
                type="button"
                aria-label={`Убрать ${file.name}`}
                onClick={() =>
                  setValue(
                    "images",
                    images.filter((_, j) => j !== i),
                    { shouldValidate: true },
                  )
                }
              >
                <X className="size-3" />
              </button>
            </span>
          ))}
        </div>
        {images.length < MAX_IMAGES && (
          <label className="text-primary inline-flex cursor-pointer items-center gap-2 text-sm font-medium">
            <ImagePlus className="size-4" /> Добавить фото
            <input
              type="file"
              accept={IMAGE_TYPES.join(",")}
              multiple
              className="sr-only"
              onChange={(e) => {
                const files = Array.from(e.target.files ?? []);
                setValue("images", [...images, ...files], { shouldValidate: true });
                e.target.value = "";
              }}
            />
          </label>
        )}
        {errors.images && <p className="text-destructive text-xs">{errors.images.message}</p>}
      </div>
      <div className="flex gap-2">
        <Button type="submit" loading={mutation.isPending}>
          Отправить
        </Button>
        <Button type="button" variant="ghost" onClick={onDone}>
          Отмена
        </Button>
      </div>
    </form>
  );
}

export function Reviews({ slug, rating, count }: { slug: string; rating: number; count: number }) {
  const status = useAuthStore((s) => s.status);
  const [writing, setWriting] = useState(false);
  const { data, isPending, fetchNextPage, hasNextPage, isFetchingNextPage } = useInfiniteQuery({
    queryKey: ["reviews", slug],
    queryFn: ({ pageParam }) => api.reviews.list(slug, pageParam),
    initialPageParam: 1,
    getNextPageParam: (last, pages) => (last.next ? pages.length + 1 : undefined),
  });
  const reviews = data?.pages.flatMap((p) => p.results) ?? [];
  const total = data?.pages[0]?.count ?? count;

  return (
    <section id="reviews" aria-labelledby="reviews-title" className="scroll-mt-32">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <h2 id="reviews-title" className="text-2xl font-bold tracking-tight">
            Отзывы <span className="text-muted-foreground">{total}</span>
          </h2>
          {total > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold">{rating.toFixed(1)}</span>
              <Stars value={rating} size="md" />
            </div>
          )}
        </div>
        {!writing &&
          (status === "authenticated" ? (
            <Button variant="outline" onClick={() => setWriting(true)}>
              Написать отзыв
            </Button>
          ) : (
            <Button asChild variant="outline">
              <Link href="/login">Войдите, чтобы оставить отзыв</Link>
            </Button>
          ))}
      </div>

      {writing && (
        <div className="mb-6">
          <ReviewFormBlock slug={slug} onDone={() => setWriting(false)} />
        </div>
      )}

      {isPending ? (
        <div className="space-y-4">
          {[0, 1].map((i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : reviews.length === 0 ? (
        <EmptyState
          icon={<MessageSquare />}
          title="Пока нет отзывов"
          description="Купите товар и расскажите о нём первым."
        />
      ) : (
        <ul className="space-y-4">
          {reviews.map((r) => (
            <li key={r.id} className="bg-card rounded-2xl border p-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <span className="bg-primary-soft text-primary flex size-9 items-center justify-center rounded-full text-sm font-semibold">
                    {r.author[0]}
                  </span>
                  <div>
                    <p className="text-sm font-medium">{r.author}</p>
                    <Stars value={r.rating} />
                  </div>
                </div>
                <time dateTime={r.created_at} className="text-muted-foreground text-xs">
                  {formatDate(r.created_at)}
                </time>
              </div>
              <p className="mt-3 text-sm leading-relaxed">{r.text}</p>
            </li>
          ))}
        </ul>
      )}

      {hasNextPage && (
        <Button
          variant="outline"
          className="mt-4 w-full"
          onClick={() => fetchNextPage()}
          loading={isFetchingNextPage}
        >
          Показать ещё
        </Button>
      )}
    </section>
  );
}
