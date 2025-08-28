import React from 'react';
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders CORRIDORS title', () => {
  render(<App />);
  const titleElement = screen.getByRole('heading', { name: /corridors/i });
  expect(titleElement).toBeInTheDocument();
});

test('renders connection status', () => {
  render(<App />);
  const connectionStatus = screen.getByTestId('connection-status');
  expect(connectionStatus).toBeInTheDocument();
});

test('renders game settings button', () => {
  render(<App />);
  const settingsButton = screen.getByText(/game settings/i);
  expect(settingsButton).toBeInTheDocument();
});
