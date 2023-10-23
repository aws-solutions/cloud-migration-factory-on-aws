// @ts-nocheck
/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";

const NavBar = (props) => {

  const myHeaderStyle = {
    postion: 'sticky'
  }

  return (
    <div id="header" className="container-fluid aws-charcoal" style={myHeaderStyle}>
      <span className="navbar-logo" />
      <nav className="navbar navbar-expand-lg navbar-light pb-0">
        <div className="collapse navbar-collapse" id="navbarNavDropdown">
          <ul className="navbar-nav">
            {props.authenticated &&
              <li className="nav-item dropdown">
                <a className="nav-link dropdown-toggle text-title pt-2" href="." id="navbarDropdownMenuLink" onClick={props.onLoad} role="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                  {props.userName ? props.userName.split("@")[0] : 'Profile'}
                </a>
                <div className="dropdown-menu" aria-labelledby="navbarDropdownMenuLink">
                     <span onClick={props.onClick} className='dropdown-item' >
                      Change Password
                    </span>
                  <span onClick={props.onClick} className='dropdown-item' >
                      Logout
                    </span>
                </div>
              </li>
            }
          </ul>
        </div>
      </nav>

    </div>
  );
}

export default NavBar
