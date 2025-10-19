import { render, screen } from '@testing-library/react'
import Home from '@/app/page'

// Mock Next.js router and Link
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(() => ({
    push: jest.fn(),
  })),
}))

jest.mock('next/link', () => {
  const MockedLink = ({ children, href, className, ...props }: any) => (
    <a href={href} className={className} {...props}>
      {children}
    </a>
  )
  MockedLink.displayName = 'Link'
  return MockedLink
})

describe('Home page', () => {
  it('renders the main heading', () => {
    render(<Home />)
    expect(screen.getByText('Truce')).toBeInTheDocument()
  })

  it('renders the search bar', () => {
    render(<Home />)
    expect(screen.getByPlaceholderText('Enter any claim to verify with evidence and AI analysis...')).toBeInTheDocument()
  })

  it('renders the hero section with description', () => {
    render(<Home />)
    expect(screen.getByText(/A transparent system for verifying contentious claims through multi-model analysis/)).toBeInTheDocument()
  })

  it('renders the "How it Works" section', () => {
    render(<Home />)
    expect(screen.getByText('How It Works')).toBeInTheDocument()
    expect(screen.getByText('Evidence Gathering')).toBeInTheDocument()
    expect(screen.getByText('Multi-Model Analysis')).toBeInTheDocument()
    expect(screen.getByText('Transparent Results')).toBeInTheDocument()
  })

  it('renders principles section', () => {
    render(<Home />)
    expect(screen.getByText('Built on Transparency')).toBeInTheDocument()
    expect(screen.getByText('Verifiable')).toBeInTheDocument()
    expect(screen.getByText('Independent')).toBeInTheDocument()
    expect(screen.getByText('Balanced')).toBeInTheDocument()
    expect(screen.getByText('Open')).toBeInTheDocument()
  })

  it('has search functionality', () => {
    render(<Home />)
    const searchButton = screen.getByRole('button', { name: /search/i })
    expect(searchButton).toBeInTheDocument()
  })
})
