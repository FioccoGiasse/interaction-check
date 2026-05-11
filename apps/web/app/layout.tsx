import "./globals.css";

export const metadata = {
  title: "ENIA Interaction Check",
  description: "Italian healthcare interaction checking platform"
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="it">
      <body>{children}</body>
    </html>
  );
}
