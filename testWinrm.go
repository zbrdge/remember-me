package main

import (
  "github.com/zbrdge/winrm/winrm"
  "fmt"
)

func main() {
  client := winrm.NewClient("SOMEWINDOWSSERVER.cloudapp.net", "USERNAME", "PASSWORD")
  stdout, stderr, _ := client.RunWithString("ipconfig /all", "")
  fmt.Println(stdout)
  fmt.Println(stderr)
}
