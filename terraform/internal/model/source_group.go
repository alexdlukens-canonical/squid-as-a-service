package model

type SourceGroup struct {
	BaseResource
	Sources []string `json:"sources"`
}

type SourceGroupInput struct {
	Name    string   `json:"name"`
	Sources []string `json:"sources"`
}
