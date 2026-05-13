package model

type Status struct {
	DBConfigVersion      int    `json:"db_config_version"`
	AppliedConfigVersion int    `json:"applied_config_version"`
	LastReload          string `json:"last_reload"`
	LastReloadOK        bool   `json:"last_reload_ok"`
	Unit                string `json:"unit"`
}
