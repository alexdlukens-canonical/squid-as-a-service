package model

import "time"

type BaseResource struct {
	ID        string    `json:"id"`
	Service   string    `json:"service"`
	Name      string    `json:"name"`
	KeyPrefix string    `json:"key_prefix"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}
