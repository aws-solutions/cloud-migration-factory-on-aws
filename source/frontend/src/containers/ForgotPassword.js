import React, {Component} from "react";
import {Auth} from "aws-amplify";
import "./Login.css";

export default class ForgotPassword extends Component {
  constructor(props) {
    super(props);

    this.state = {
      isLoading: false,
      email: "",
      password: "",
      code: ""
    };
  }

  validateForm() {
    return this.state.email.length > 0 && this.state.password.length > 0 && this.state.code.length > 0;
  }

  handleChange = event => {
    this.setState({
      [event.target.id]: event.target.value
    });
  }

  handleSubmit = async event => {
    event.preventDefault();

    this.setState({isLoading: true});

    try {
      await Auth.forgotPasswordSubmit(this.state.email, this.state.code, this.state.password);
      alert("Password saved successfully!");
      this.props.history.push("/login");
    } catch (e) {
      alert(e.message);
      this.setState({isLoading: false});
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
                <input id="email" type="text" onChange={this.handleChange} className="form-control form-control-sm" ref="email" placeholder="Username"/>
              </div>
              <div className="form-group">
                <input id="code" type="text" onChange={this.handleChange} className="form-control form-control-sm" placeholder="Password Reset Code" ref="appName"/>
              </div>
              <div className="form-group">
                <input id="password" type="password" onChange={this.handleChange} className="form-control form-control-sm" placeholder="New Password" ref="appName"/>
              </div>
              <div className="form-group text-center">
                <input
                  style={{width:"100%"}}
                  className="btn btn-primary btn-outline btn-aws-charcoal mt-3 mb-2 mr-3"
                  type="submit"
                  value="Reset Password"
                />
              </div>
            </form>

          </div>

      </div>
    </div>);
  }
}
