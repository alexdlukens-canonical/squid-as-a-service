package model

type DestinationConfig struct {
	BaseResource
	Dst        string   `json:"dst"`
	Type       string   `json:"type"`
	Ports      []int    `json:"ports,omitempty"`
	PortGroups []string `json:"port_groups,omitempty"`
}

type DestinationConfigInput struct {
	Name       string   `json:"name"`
	Dst        string   `json:"dst"`
	Type       string   `json:"type"`
	Ports      []int    `json:"ports,omitempty"`
	PortGroups []string `json:"port_groups,omitempty"`
}
