import "./globals.css";

export const metadata = {
  title: "Interaction Check Demo V1 · SP",
  description: "Demo SP per verifica documentale di interazioni e report"
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
