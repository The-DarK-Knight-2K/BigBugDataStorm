const { createClient } = require('@libsql/client');
const Database = require('better-sqlite3');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '../.env') });

async function migrate() {
  const localDb = new Database(path.join(__dirname, '../data/outlets.db'));
  const tursoDb = createClient({
    url: process.env.TURSO_DATABASE_URL,
    authToken: process.env.TURSO_AUTH_TOKEN
  });

  console.log("Fetching local tables...");
  const tables = localDb.prepare("SELECT name FROM sqlite_master WHERE type='table'").all();
  
  for (const { name: tableName } of tables) {
    if (tableName === 'sqlite_sequence') continue;
    
    console.log(`\nMigrating table: ${tableName}`);
    
    // Get schema
    const schema = localDb.prepare(`SELECT sql FROM sqlite_master WHERE type='table' AND name=?`).get(tableName).sql;
    // Drop table if exists on Turso
    try { await tursoDb.execute(`DROP TABLE IF EXISTS ${tableName}`); } catch (e) {}
    // Create table on Turso
    await tursoDb.execute(schema);
    
    const rows = localDb.prepare(`SELECT * FROM ${tableName}`).all();
    console.log(`Found ${rows.length} rows in ${tableName}`);
    
    if (rows.length === 0) continue;
    
    // Batch insert
    const keys = Object.keys(rows[0]);
    const placeholders = keys.map(() => '?').join(',');
    const insertSql = `INSERT INTO ${tableName} (${keys.join(',')}) VALUES (${placeholders})`;
    
    const BATCH_SIZE = 1000;
    for (let i = 0; i < rows.length; i += BATCH_SIZE) {
      const batch = rows.slice(i, i + BATCH_SIZE);
      const statements = batch.map(row => ({
        sql: insertSql,
        args: keys.map(k => row[k])
      }));
      
      await tursoDb.batch(statements, 'write');
      process.stdout.write(`\r  Inserted ${Math.min(i + BATCH_SIZE, rows.length)}/${rows.length} rows`);
    }
    console.log();
  }
  
  console.log("\nMigration complete! Your local database is now in Turso.");
}

migrate().catch(console.error);
