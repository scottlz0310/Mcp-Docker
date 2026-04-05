// Package store manages the SQLite trigger_log database used to track
// when Copilot reviews were requested and completed.
package store

import (
	"database/sql"
	"time"

	_ "modernc.org/sqlite"
)

const schema = `
CREATE TABLE IF NOT EXISTS trigger_log (
    id           INTEGER PRIMARY KEY,
    owner        TEXT    NOT NULL,
    repo         TEXT    NOT NULL,
    pr           INTEGER NOT NULL,
    trigger      TEXT    NOT NULL,
    requested_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    completed_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_trigger_log_pr ON trigger_log(owner, repo, pr);
`

// DB wraps a SQLite database for trigger_log operations.
type DB struct {
	db *sql.DB
}

// Open opens (or creates) the SQLite database at path and applies the schema.
func Open(path string) (*DB, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	// Limit to a single connection to avoid "database is locked" errors with SQLite.
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)
	// Enable WAL mode for better concurrent access.
	if _, err := db.Exec("PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;"); err != nil {
		db.Close()
		return nil, err
	}
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, err
	}
	return &DB{db: db}, nil
}

// Close releases the database connection.
func (d *DB) Close() error { return d.db.Close() }

// TriggerEntry is a row from trigger_log.
type TriggerEntry struct {
	ID          int64
	Trigger     string    // "MANUAL" or "AUTO"
	RequestedAt time.Time // when the review was requested
	CompletedAt *time.Time
}

// Insert adds a new trigger_log entry and returns the assigned ID.
func (d *DB) Insert(owner, repo string, pr int, trigger string) (int64, error) {
	res, err := d.db.Exec(
		`INSERT INTO trigger_log (owner, repo, pr, trigger) VALUES (?, ?, ?, ?)`,
		owner, repo, pr, trigger,
	)
	if err != nil {
		return 0, err
	}
	return res.LastInsertId()
}

// GetLatest returns the most recent trigger_log entry for the given PR,
// or nil if none exists.
func (d *DB) GetLatest(owner, repo string, pr int) (*TriggerEntry, error) {
	row := d.db.QueryRow(
		`SELECT id, trigger, requested_at, completed_at
		 FROM trigger_log
		 WHERE owner = ? AND repo = ? AND pr = ?
		 ORDER BY requested_at DESC, id DESC
		 LIMIT 1`,
		owner, repo, pr,
	)
	var e TriggerEntry
	var requestedAtUnix int64
	var completedAtUnix sql.NullInt64
	if err := row.Scan(&e.ID, &e.Trigger, &requestedAtUnix, &completedAtUnix); err != nil {
		if err == sql.ErrNoRows {
			return nil, nil
		}
		return nil, err
	}
	e.RequestedAt = time.Unix(requestedAtUnix, 0)
	if completedAtUnix.Valid {
		t := time.Unix(completedAtUnix.Int64, 0)
		e.CompletedAt = &t
	}
	return &e, nil
}

// UpdateCompletedAt marks the given trigger_log row as completed (now).
// The update is conditional on completed_at IS NULL so the original completion
// time is preserved across retries or concurrent calls.
func (d *DB) UpdateCompletedAt(id int64) error {
	_, err := d.db.Exec(
		`UPDATE trigger_log
		 SET completed_at = strftime('%s','now')
		 WHERE id = ? AND completed_at IS NULL`,
		id,
	)
	return err
}

// HasPending returns true if there is an unfinished trigger_log entry for the PR.
func (d *DB) HasPending(owner, repo string, pr int) (bool, error) {
	var count int
	err := d.db.QueryRow(
		`SELECT COUNT(*) FROM trigger_log
		 WHERE owner = ? AND repo = ? AND pr = ? AND completed_at IS NULL`,
		owner, repo, pr,
	).Scan(&count)
	return count > 0, err
}
