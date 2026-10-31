import { SearchX } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="container-page flex flex-col items-center py-24 text-center">
      <span className="bg-primary-soft text-primary flex size-16 items-center justify-center rounded-full">
        <SearchX className="size-7" />
      </span>
      <p className="text-primary mt-6 text-sm font-semibold">Ошибка 404</p>
      <h1 className="mt-2 text-3xl font-bold tracking-tight">Такой страницы нет</h1>
      <p className="text-muted-foreground mt-2 max-w-md">
        Возможно, товар сняли с продажи или в адресе опечатка. Попробуйте поиск или загляните в
        каталог.
      </p>
      <div className="mt-8 flex gap-2">
        <Button asChild>
          <Link href="/">На главную</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/catalog">В каталог</Link>
        </Button>
      </div>
    </div>
  );
}
