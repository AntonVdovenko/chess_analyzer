import { render, screen } from '@testing-library/react';
import App from './App';

test('renders the study plan generator heading', () => {
  render(<App />);
  expect(screen.getByRole('heading', { name: /study plan generator/i })).toBeInTheDocument();
});
