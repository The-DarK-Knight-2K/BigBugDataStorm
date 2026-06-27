import { createClient, Client } from '@libsql/client';

/**
 * Global variable for the database connection.
 * We use `globalThis` to preserve the connection across Next.js hot reloads.
 */
const globalForDb = globalThis as unknown as {
  db: Client | undefined;
};

// Initialize the connection or reuse the existing one
const db = globalForDb.db ?? createClient({
  url: process.env.TURSO_DATABASE_URL!,
  authToken: process.env.TURSO_AUTH_TOKEN!,
});

if (process.env.NODE_ENV !== 'production') {
  globalForDb.db = db;
}

export default db;
