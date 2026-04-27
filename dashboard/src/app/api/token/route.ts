import { auth } from "@/auth";
import { NextResponse } from "next/server";

export async function GET() {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  
  // Note: In Auth.js v5, the session cookie IS the JWT.
  // We can't easily get the raw string from 'auth()' but we can read the cookie.
  // However, for simplicity in this task, let's assume we pass the session data
  // or a signed version of it.
  
  return NextResponse.json({ session });
}
