import React, {useState} from "react";
import { Auth } from "aws-amplify";

import {useLocation, useNavigate, useParams} from "react-router-dom";
import {Box, Button, Container, FormField, Grid, Header, Input, SpaceBetween} from "@awsui/components-react";

const ChangePassword = (props) => {
  let location = useLocation()
  let navigate = useNavigate();
  let params = useParams();

  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  function validateForm() {
    return email.length > 0 && oldPassword.length > 0 && newPassword.length > 0;
  }

  const handleChange = event => {
    switch(event.target.id) {
      case 'email': {
        setEmail(event.target.value)
        break;
      }
      case 'newpassword': {
        setNewPassword(event.target.value)
        break;
      }
      case 'oldpassword': {
        setOldPassword(event.target.value)
        break;
      }
    }
  }

  const handleSubmit = async event => {
    event.preventDefault();

    setIsLoading(true);

    try {
      const user = await Auth.signIn(email, oldPassword);

      if (user.challengeName === 'NEW_PASSWORD_REQUIRED') {
        //? What is this? const { requiredAttributes } = user.challengeParam; // the array of required attributes, e.g ['email', 'phone_number']
        await Auth.completeNewPassword(user, newPassword);
      }
      else {
        const authUser = await Auth.currentAuthenticatedUser();
        await Auth.changePassword(authUser, oldPassword, newPassword);
      }
      alert("Password changed successfully!");
      //this.props.userHasAuthenticated(true);
      navigate("/");
    } catch (e) {
      if (e.message === 'User does not exist.') {
        alert('Incorrect username or password.');
      }
      else{
        alert(e.message);
      }
      setIsLoading(false);
    }
  }

  return (
      <Box margin="xxl" padding="xxl">
        <Container
          header={
            <Header
              variant="h2"
            >
              Change Password
            </Header>
          }
        >
          <SpaceBetween size={'xl'} direction={'vertical'}>
            <SpaceBetween size={'xxs'} direction={'vertical'}>
              <FormField
                key={'username'}
                label={'Username'}
              >
                <Input
                  value={email}
                  onChange={event => setEmail(event.detail.value)}
                />
              </FormField>

              <FormField
                key={'oldPassword'}
                label={'Current Password'}
              >
                <Input
                  value={oldPassword}
                  onChange={event => setOldPassword(event.detail.value)}
                  type="password"
                />
              </FormField>

              <FormField
                key={'password'}
                label={'New Password'}
                errorText={newPassword !== confirmPassword ? 'Passwords do not match.' : null}
              >
                <Input
                  value={newPassword}
                  onChange={event => setNewPassword(event.detail.value)}
                  type="password"
                />
              </FormField>

              <FormField
                key={'confirmPassword'}
                label={'Confirm New Password'}
              >
                <Input
                  value={confirmPassword}
                  onChange={event => setConfirmPassword(event.detail.value)}
                  type="password"
                />
              </FormField>
            </SpaceBetween>
            <Box float={'right'}>
              <SpaceBetween size={'xs'} direction={'horizontal'}>
                <Button disabled={email && oldPassword && newPassword && confirmPassword && newPassword === confirmPassword ? false : true} variant={'primary'} onClick={handleSubmit}>Change Password</Button>
                <Button onClick={() => navigate("/")}>Cancel</Button>
              </SpaceBetween>
            </Box>
          </SpaceBetween>
        </Container>
      </Box>
  );

}

export default ChangePassword

// export default class ChangePassword extends Component {
//   constructor(props) {
//     super(props);
//
//     this.state = {
//       isLoading: false,
//       email: "",
//       oldPassword: "",
//       newPassword: ""
//     };
//   }
//
//   validateForm() {
//     return this.state.email.length > 0 && this.state.oldPassword.length > 0 && this.state.newPassword.length > 0;
//   }
//
//   handleChange = event => {
//     this.setState({
//       [event.target.id]: event.target.value
//     });
//   }
//
//   handleSubmit = async event => {
//     event.preventDefault();
//
//     this.setState({isLoading: true});
//
//     try {
//       const user = await Auth.signIn(this.state.email, this.state.oldPassword);
//
//       if (user.challengeName === 'NEW_PASSWORD_REQUIRED') {
//         //? What is this? const { requiredAttributes } = user.challengeParam; // the array of required attributes, e.g ['email', 'phone_number']
//         await Auth.completeNewPassword(user, this.state.newPassword);
//       } else {
//         const authUser = await Auth.currentAuthenticatedUser();
//         await Auth.changePassword(authUser, this.state.oldPassword, this.state.newPassword);
//       }
//       alert("Password changed successfully!");
//       //this.props.userHasAuthenticated(true);
//       this.props.history.push("/");
//     } catch (e) {
//       if (e.message === 'User does not exist.') {
//         alert('Incorrect username or password.');
//       } else {
//         alert(e.message);
//       }
//       this.setState({isLoading: false});
//     }
//   }
//
//
// }
//
//
//
//   render() {
//     return (
//       <div className="container pt-5">
//         <div className="login mx-auto login-box p-0 m-0">
//           <div className="aws-charcoal login-header p-0 m-0" style={{height:"65px"}} >
//             <span style={{height:"65px"}} className="navbar-logo navbar-logo-login pt-5"/>
//             <span className="login-title"><h4>Migration Factory</h4></span>
//           </div>
//
//           <div className="mt-5 px-4">
//
//               <form onSubmit={this.handleSubmit}>
//
//                   <div className="form-group">
//                   <label htmlfor="emailaddress">Username</label>
//                     <input
//                       id="email"
//                       type="text"
//                       onChange={this.handleChange}
//                       className="form-control form-control-sm"
//                       ref="email"
//                       placeholder="Username"
//                     />
//                   </div>
//                   <div className="form-group">
//                     <label htmlfor="currentpwd">Current Password</label>
//                     <input
//                       id="oldPassword"
//                       type="password"
//                       onChange={this.handleChange}
//                       className="form-control form-control-sm"
//                       placeholder="Current Password"
//                       ref="appName"
//                     />
//                   </div>
//                   <div className="form-group">
//                     <label htmlfor="newpwd">New Password</label>
//                     <input
//                       id="newPassword"
//                       type="password"
//                       onChange={this.handleChange}
//                       className="form-control form-control-sm"
//                       placeholder="New Password"
//                       ref="appName"
//                     />
//                   </div>
//                   <div className="form-group text-center">
//                     <input
//                       style={{width:"100%"}}
//                       className="btn btn-primary btn-outline btn-aws-charcoal mt-3 mb-2 mr-3"
//                       type="submit"
//                       value="Change Password"
//                     />
//
//                   </div>
//               </form>
//             </div>
//
//         </div>
//       </div>
//     );
//   }
// }
