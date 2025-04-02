import type { Metadata } from 'next';
import { Press_Start_2P } from 'next/font/google';
import { Providers } from './providers';
import './globals.css';

const pressStart2P = Press_Start_2P({
  weight: '400',
  subsets: ['latin'],
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Pokémon Gym',
  description: 'Watch AI playing Pokémon Red',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={pressStart2P.className}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
} 