import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';

describe('Debug Test', () => {
  it('should render simple component', () => {
    const SimpleComponent = () => <div>Test Content</div>;
    const { container } = render(<SimpleComponent />);
    console.log('Container HTML:', container.innerHTML);
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });
});
