import React, { Component } from "react";
import { Auth } from "aws-amplify";
import "./Login.css";

export default class ForgotPassword extends Component {
  constructor(props) {
    super(props);

    this.state = {
      isLoading: false,
      email: "",
      oldPassword: "",
      newPassword: ""
    };
  }

  validateForm() {
    return this.state.email.length > 0 && this.state.oldPassword.length > 0 && this.state.newPassword.length > 0;
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
    const user = await Auth.signIn(this.state.email, this.state.oldPassword);

    if (user.challengeName === 'NEW_PASSWORD_REQUIRED') {
        //? What is this? const { requiredAttributes } = user.challengeParam; // the array of required attributes, e.g ['email', 'phone_number']
        await Auth.completeNewPassword(user,this.state.newPassword);
    }
    else {
      const authUser = await Auth.currentAuthenticatedUser();
      await Auth.changePassword(authUser, this.state.oldPassword, this.state.newPassword);
    }
    alert("Password changed successfully!");
    this.props.userHasAuthenticated(true);
    this.props.history.push("/");
 } catch (e) {
    if (e.message === 'User does not exist.') {
      alert('Incorrect username or password.');
    }
    else{
      alert(e.message);
    }
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
                  <label htmlfor="emailaddress">Username</label>
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
                    <label htmlfor="currentpwd">Current Password</label>
                    <input
                      id="oldPassword"
                      type="password"
                      onChange={this.handleChange}
                      className="form-control form-control-sm"
                      placeholder="Current Password"
                      ref="appName"
                    />
                  </div>
                  <div className="form-group">
                    <label htmlfor="newpwd">New Password</label>
                    <input
                      id="newPassword"
                      type="password"
                      onChange={this.handleChange}
                      className="form-control form-control-sm"
                      placeholder="New Password"
                      ref="appName"
                    />
                  </div>
                  <div className="form-group text-center">
                    <input
                      style={{width:"100%"}}
                      className="btn btn-primary btn-outline btn-aws-charcoal mt-3 mb-2 mr-3"
                      type="submit"
                      value="Change Password"
                    />

                  </div>
              </form>
            </div>

        </div>
      </div>
    );
  }
}
