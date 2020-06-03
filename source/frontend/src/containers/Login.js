import React, { Component } from "react";
import { Auth } from "aws-amplify";
import "./Login.css";


export default class Login extends Component {
  constructor(props) {
    super(props);

    this.state = {
      isLoading: false,
      email: "",
      password: ""
    };
  }

  validateForm() {
    return this.state.email.length > 0 && this.state.password.length > 0;
  }

  handleChange = event => {
    this.setState({
      [event.target.id]: event.target.value
    });
  }

  handleSubmit = async event => {
    event.preventDefault();

    this.setState({ isLoading: true });

    try {
      if (this.state.password === '' || this.state.email === '') {
        alert('Incorrect username or password.');
      }
      else {
      const user = await Auth.signIn(this.state.email, this.state.password);
      if (user.challengeName === 'NEW_PASSWORD_REQUIRED') {
              this.props.history.push("/change/pwd");
          }
          else {
            this.props.userHasAuthenticated(true);
            this.props.history.push("/");
          }
      }
    } catch (e) {
      if (e.message === 'User does not exist.') {
        alert('Incorrect username or password.');
      }
      else {
      alert(e.message);
      }
      this.setState({ isLoading: false });
    }
  }

  handleForgotPassword = async event => {
    event.preventDefault();

    this.setState({ isLoading: true });

    try {
      await Auth.forgotPassword(this.state.email);
      this.props.history.push("/forgot/pwd");
    } catch (e) {
      alert(e.message);
      this.setState({ isLoading: false });
    }
  }

  render() {
    return (
      <div className="container pt-5">
        <div className="login mx-auto login-box p-0 m-0">
          <div className="aws-charcoal login-header p-0 m-0" style={{height:"65px"}} >
            <span style={{height:"65px"}} className="navbar-logo navbar-logo-login pt-5"/>
            <span className="login-title"><h4>Migration Factory</h4></span>
          </div>

          <div className="mt-5 px-4">
              <form onSubmit={this.handleSubmit}>

                  <div className="form-group">
                    <input
                      id="email"
                      type="text"
                      onChange={this.handleChange}
                      className="form-control form-control-sm"
                      ref="email"
                      placeholder="Username"
                    />
                  </div>
                  <div className="form-group">
                    <input
                      id="password"
                      type="password"
                      onChange={this.handleChange}
                      className="form-control form-control-sm"
                      placeholder="Password"
                      ref="appName"
                    />
                  </div>
                  <div className="form-group text-center pt-2">
                    <input
                      style={{width:"100%"}}
                      className="btn btn-primary btn-outline btn-aws-charcoal mt-3 mr-3"
                      type="submit"
                      value="Login"
                    />
                  </div>
              </form>
          </div>

          <div className="mt-4 px-4 pb-4">
            <a href="." style={{fontSize:".8em"}} onClick={this.handleForgotPassword}>Forgot your password?</a>
          </div>

        </div>
      </div>
    );
  }
}
