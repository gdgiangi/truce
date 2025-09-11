import { NextRequest, NextResponse } from "next/server";

export async function POST(
  request: NextRequest,
  { params }: { params: { topic: string } }
) {
  const adjudicatorUrl = process.env.ADJUDICATOR_API_URL || 'http://localhost:8000';
  
  try {
    const body = await request.json();
    
    const response = await fetch(`${adjudicatorUrl}/consensus/${params.topic}/votes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to submit vote' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('Error submitting vote:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
