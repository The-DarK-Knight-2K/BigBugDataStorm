import Database from 'better-sqlite3';
import path from 'path';

// Construct the absolute path to the SQLite database
const dbPath = path.resolve(process.cwd(), 'data/outlets.db');

/**
 * Global variable for the database connection.
 * We use `globalThis` to preserve the connection across Next.js hot reloads.
 */
const globalForDb = globalThis as unknown as {
  db: Database.Database | undefined;
};

// Initialize the connection or reuse the existing one
const db = globalForDb.db ?? new Database(dbPath, { 
  verbose: process.env.NODE_ENV !== 'production' ? console.log : undefined 
});

if (process.env.NODE_ENV !== 'production') {
  globalForDb.db = db;
}

// Enable Write-Ahead Logging for better concurrent read/write performance
db.pragma('journal_mode = WAL');

export default db;
