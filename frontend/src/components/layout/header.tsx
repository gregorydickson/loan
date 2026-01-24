interface HeaderProps {
  title?: string;
}

export function Header({ title }: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 hidden h-16 items-center border-b bg-background px-6 md:flex">
      <h1 className="text-lg font-semibold">{title}</h1>
    </header>
  );
}
