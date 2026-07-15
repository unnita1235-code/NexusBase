import { auth } from "@/auth";

export default auth((req) => {
  const isLoggedIn = !!req.auth;
  const path = req.nextUrl.pathname;
  const isAuthPage = path.startsWith("/login") || path.startsWith("/register");
  const isApi = path.startsWith("/api/auth") || path.startsWith("/api/cron");
  const isPublic = isAuthPage || isApi || path === "/";

  if (isPublic) return;

  if (!isLoggedIn) {
    return Response.redirect(new URL("/login", req.nextUrl.origin));
  }
});

export const config = {
  matcher: ["/((?!api/auth|_next/static|_next/image|favicon.ico).*)"],
};
