import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import GoogleProvider from "next-auth/providers/google";

// This is where we define how NextAuth communicates with our FastAPI backend.
const handler = NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/login`, {
          method: 'POST',
          body: JSON.stringify(credentials),
          headers: { 'Content-Type': 'application/json' }
        });
        const user = await res.json();

        if (res.ok && user) {
          // Return the user object which will include tokens
          return user;
        }
        return null;
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user, account }) {
      // On sign-in, persist the tokens from our backend to the NextAuth token
      if (account && user) {
        return {
          ...token,
          accessToken: user.access_token,
          refreshToken: user.refresh_token,
        };
      }
      // TODO: Add refresh token rotation logic here
      return token;
    },
    async session({ session, token }) {
      // Expose the tokens to the client-side session
      session.accessToken = token.accessToken;
      session.error = token.error;
      return session;
    },
  },
  pages: {
    signIn: '/auth/login',
  }
});

export { handler as GET, handler as POST };