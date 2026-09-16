package main

import (
	"log"

	"github.com/zentrix-app/zentrix-backend-go-temp/config"
	"github.com/zentrix-app/zentrix-backend-go-temp/internal/app"
)

func main() {
	// Configuration
	cfg, err := config.NewConfig()
	if err != nil {
		log.Fatalf("Config error: %s", err)
	}

	// Run
	app.Run(cfg)
}
