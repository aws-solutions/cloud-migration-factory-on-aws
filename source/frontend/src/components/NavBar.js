import React from "react";

export default class NavBar extends React.Component {
  render() {
    const selection = this.props.selection;
    
    return (
      <div className="container-fluid aws-charcoal">
        <span className="navbar-logo" />
        <span className="navbar-brand text-title"><h4>Migration Factory</h4></span>
        <nav className="navbar navbar-expand-lg navbar-light pb-0">
          <div className="collapse navbar-collapse" id="navbarNavDropdown">
            <ul className="navbar-nav">
              <li className="nav-item dropdown">
                <a className="nav-link dropdown-toggle text-title pt-2" href="." id="navbarDropdownMenuLink" onClick={this.props.onLoad} role="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                    {selection}
                </a>
                <div className="dropdown-menu" aria-labelledby="navbarDropdownMenuLink">
                  <span onClick={this.props.onClick} className={'dropdown-item '+((selection==='Pipeline')&&'hide')} >Pipeline</span>
                  <span onClick={this.props.onClick} className={'dropdown-item '+((selection==='Admin')&&'hide')} >Admin</span>
                  <span onClick={this.props.onClick} className={'dropdown-item '+((selection==='Resource List')&&'hide')} >Resource List</span>
                  <span onClick={this.props.onClick} className={'dropdown-item '+((selection==='Tools')&&'hide')} >Tools</span>
                  <span onClick={this.props.onClick} className='dropdown-item' >Logout</span>
                </div>
              </li>
            </ul>
          </div>
        </nav>

      </div>
    );
  }
};
