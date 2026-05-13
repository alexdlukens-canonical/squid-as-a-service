package model

type PortGroup struct {
	BaseResource
	Ports []int `json:"ports"`
}

type PortGroupInput struct {
	Name  string `json:"name"`
	Ports []int  `json:"ports"`
}
