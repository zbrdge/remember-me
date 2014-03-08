package main

import (
	"fmt"
	"bytes"
	"bufio"
	"strings"
	"os"
	"code.google.com/p/go.crypto/ssh"
	"github.com/howeyc/gopass"
)

var (
	server = "localhost"
)

type userPass string
func (p userPass) Password(n string) (string, error) {
	fmt.Printf("Enter password for user %s: ", n)
	pass := gopass.GetPasswd()
	return string(pass), nil
}

func main() {

	fmt.Printf("Please enter a username: ")
	reader := bufio.NewReader(os.Stdin)
	username, _ := reader.ReadString('\n')
	username = strings.TrimSpace(username)

	// An SSH client is represented with a ClientConn. Currently only
	// the "password" authentication method is supported.
	//
	// To authenticate with the remote server you must pass at least one
	// implementation of ClientAuth via the Auth field in ClientConfig.
	config := &ssh.ClientConfig{
	    User: username,
	    Auth: []ssh.ClientAuth{
		// ClientAuthPassword wraps a ClientPassword implementation
		// in a type that implements ClientAuth.
		ssh.ClientAuthPassword(userPass(username)),
	    },
	}

	client, err := ssh.Dial("tcp", server+":22", config)
	if err != nil {
	    panic("Failed to dial: " + err.Error())
	}

	// Each ClientConn can support multiple interactive sessions,
	// represented by a Session.
	session, err := client.NewSession()
	if err != nil {
	    panic("Failed to create session: " + err.Error())
	}
	defer session.Close()

	// Once a Session is created, you can execute a single command on
	// the remote side using the Run method.
	var b bytes.Buffer
	session.Stdout = &b
	if err := session.Run("/usr/bin/uname"); err != nil {
	    panic("Failed to run: " + err.Error())
	}

	fmt.Println(b.String())
}
