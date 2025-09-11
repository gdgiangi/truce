import { NextRequest, NextResponse } from "next/server";

export async function GET(
  request: NextRequest,
  { params }: { params: { topic: string } }
) {
  const adjudicatorUrl = process.env.ADJUDICATOR_API_URL || 'http://localhost:8000';
  
  try {
    const response = await fetch(`${adjudicatorUrl}/consensus/${params.topic}/summary`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Topic not found' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
    
  } catch (error) {
    console.error('Error fetching consensus summary:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
