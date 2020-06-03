import React from "react";

export class List extends React.Component {
  render() {

    // options will come in as a string with value seperated by new line
    var options = this.props.options.split(",");

    // default selection is none unless attribute has existing value
    var value = "none";
    if (this.props.value !== undefined && this.props.options.includes(this.props.value)){
      value = this.props.value;
    }

    return (
      <div className="form-group">
        <label>{this.props.label}:</label>
        <select disabled={this.props.disabled} value={value} onChange={this.props.onChange(this.props.attr_name,'list')} className="form-control form-control-sm">
          <option value="none" disabled> -- select an option -- </option>
          {options.map((item, index) => {
            return (
              <option key={item} value={item}>{item}</option>
            )
          })}
        </select>
      </div>
    )
  }
}

export class String extends React.Component {
  render() {

    // Prevent value from being undefined
    var value = this.props.value;
    if (value === undefined) {
      value = ''
    }

    return (
      <div key={this.props.attr_name} className="form-group">
        <label htmlFor={this.props.attr_name}>{this.props.label}:</label>
        <input disabled={this.props.disabled} type="string" value={value} onChange={this.props.onChange(this.props.attr_name,'string')} className="form-control form-control-sm"/>
      </div>
    )
  }
}

export class MultiValueString extends React.Component {
  render() {

    // Prevent value from being undefined
    var value = this.props.value;
    if (value === undefined) {
      value = ''
    }

    return (
      <div key={this.props.attr_name} className="form-group">
        <label htmlFor={this.props.attr_name}>{this.props.label}:</label>
        <input disabled={this.props.disabled} type="string" value={value} onChange={this.props.onChange(this.props.attr_name,'multivalue-string')} className="form-control form-control-sm"/>
      </div>
    )
  }
}

export class TextArea extends React.Component {
  render() {

    // Prevent value from being undefined
    var value = this.props.value;
    if (value === undefined) {
      value = ''
    }

    return (
      <div key={this.props.attr_name} className="form-group">
        <label htmlFor={this.props.attr_name}>{this.props.label}:</label>
        <textarea disabled={this.props.disabled} type="string" value={value} onChange={this.props.onChange(this.props.attr_name,'textarea')} className="form-control"></textarea>
      </div>
    )
  }
}

export class Tag extends React.Component {
  render() {

    // Prevent value from being undefined
    var value = this.props.value;
    if (value === undefined) {
      value = ''
    }

    return (
      <div key={this.props.attr_name} className="form-group">
        <label htmlFor={this.props.attr_name}>{this.props.label}:</label>
        <textarea disabled={this.props.disabled} type="string" value={value} onChange={this.props.onChange(this.props.attr_name,'tag')} className="form-control"></textarea>
      </div>
    )
  }
}

export class CheckBox extends React.Component {
  render() {

    // Prevent value from being undefined
    var value = this.props.value;
    if (value==='' || value===undefined){
      value=false
    }

    return (
      <div key={this.props.attr_name} className="form-check pt-2 pb-4">
        <input disabled={this.props.disabled} type="checkbox" value={true} checked={Boolean(value)} onChange={this.props.onChange(this.props.attr_name,'checkbox')} className="form-check-input"/>
        <label className="form-check-label" htmlFor={this.props.attr_name}>{this.props.label}</label>
      </div>
    )
  }
}
