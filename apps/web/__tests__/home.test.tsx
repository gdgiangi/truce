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
    expect(screen.getByText('Welcome to')).toBeInTheDocument()
    expect(screen.getByText('Truce')).toBeInTheDocument()
  })

  it('renders the search bar', () => {
    render(<Home />)
    expect(screen.getByPlaceholderText('Search claims or evidence')).toBeInTheDocument()
  })

  it('renders the hero section with description', () => {
    render(<Home />)
    expect(screen.getByText(/A transparent system for de-escalating dialogue/)).toBeInTheDocument()
  })

  it('renders the "How it Works" section', () => {
    render(<Home />)
    expect(screen.getByText('How Truce Works')).toBeInTheDocument()
    expect(screen.getByText('Provenance')).toBeInTheDocument()
    expect(screen.getByText('Multi-Model Analysis')).toBeInTheDocument()
    expect(screen.getByText('Consensus Finding')).toBeInTheDocument()
  })

  it('renders demo section with claim analysis', () => {
    render(<Home />)
    expect(screen.getByText('Live Demo')).toBeInTheDocument()
    expect(screen.getByText('Claim Analysis')).toBeInTheDocument()
    expect(screen.getByText(/Violent crime in Canada is rising/)).toBeInTheDocument()
  })

  it('renders demo section with consensus board', () => {
    render(<Home />)
    expect(screen.getAllByText('Consensus Board')).toHaveLength(2) // Link and heading
    expect(screen.getByText('Find common ground on Canadian crime policy')).toBeInTheDocument()
  })

  it('renders principles section', () => {
    render(<Home />)
    expect(screen.getByText('Our Principles')).toBeInTheDocument()
    expect(screen.getByText('Transparency')).toBeInTheDocument()
    expect(screen.getByText('Reproducibility')).toBeInTheDocument()
    expect(screen.getByText('De-escalation')).toBeInTheDocument()
    expect(screen.getByText('Consensus')).toBeInTheDocument()
  })

  it('has correct links for demo claim and consensus board', () => {
    render(<Home />)
    const demoClaimLink = screen.getByRole('link', { name: /view demo claim/i })
    const consensusBoardLink = screen.getByRole('link', { name: /consensus board/i })
    
    expect(demoClaimLink).toHaveAttribute('href', '/claim/violent-crime-in-canada-is-rising')
    expect(consensusBoardLink).toHaveAttribute('href', '/consensus/canada-crime')
  })

  it('has correct link for claim analysis button', () => {
    render(<Home />)
    const claimAnalysisLink = screen.getByRole('link', { name: /view claim analysis/i })
    expect(claimAnalysisLink).toHaveAttribute('href', '/claim/violent-crime-in-canada-is-rising')
  })

  it('has correct link for join discussion button', () => {
    render(<Home />)
    const joinDiscussionLink = screen.getByRole('link', { name: /join discussion/i })
    expect(joinDiscussionLink).toHaveAttribute('href', '/consensus/canada-crime')
  })
})
