import { redirect } from 'next/navigation';

export default function HomePage() {
  redirect('/dashboard');
  // return null; // redirect ideally handles this, but good practice for components that might render nothing.
} 